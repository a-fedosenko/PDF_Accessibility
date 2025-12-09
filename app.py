import aws_cdk as cdk
from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as lambda_,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_logs as logs,
    aws_ecr_assets as ecr_assets,
    aws_cloudwatch as cloudwatch,
    aws_secretsmanager as secretsmanager,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    aws_cloudwatch_actions as cw_actions,
    aws_dynamodb as dynamodb
)
from constructs import Construct
import platform
import datetime
import os

class PDFAccessibility(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # S3 Bucket
        bucket = s3.Bucket(self, "pdfaccessibilitybucket1",
                          encryption=s3.BucketEncryption.S3_MANAGED,
                          enforce_ssl=True,
                          cors=[s3.CorsRule(
                              allowed_headers=["*"],
                              allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.HEAD, s3.HttpMethods.PUT, s3.HttpMethods.POST, s3.HttpMethods.DELETE],
                              allowed_origins=["*"],
                              exposed_headers=[]
                          )])

        # SNS Topic for Quota Alerts
        quota_alert_topic = sns.Topic(
            self, "QuotaAlertTopic",
            display_name="PDF Accessibility Quota Alerts",
            topic_name="pdf-accessibility-quota-alerts"
        )

        # Add email subscription (you can configure this via environment variable)
        alert_email = os.environ.get('QUOTA_ALERT_EMAIL')
        if alert_email:
            quota_alert_topic.add_subscription(
                sns_subscriptions.EmailSubscription(alert_email)
            )

        # DynamoDB Table for Usage Tracking
        usage_tracking_table = dynamodb.Table(
            self, "UsageTrackingTable",
            table_name="pdf-accessibility-usage",
            partition_key=dynamodb.Attribute(
                name="api_name",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="period",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            point_in_time_recovery=True
        )

        python_image_asset = ecr_assets.DockerImageAsset(self, "PythonImage",
                                                         directory="docker_autotag",
                                                        platform=ecr_assets.Platform.LINUX_AMD64)

        javascript_image_asset = ecr_assets.DockerImageAsset(self, "JavaScriptImage",
                                                             directory="javascript_docker",
                                                             platform=ecr_assets.Platform.LINUX_AMD64)
        # VPC with Public and Private Subnets
        vpc = ec2.Vpc(self, "MyVpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PUBLIC,
                    name="Public",
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    name="Private",
                    cidr_mask=24,
                ),
            ]
        )

        # ECS Cluster
        cluster = ecs.Cluster(self, "FargateCluster", vpc=vpc)

        ecs_task_execution_role = iam.Role(self, "EcsTaskRole",
                                 assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
                                 managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ])

        # Allow ECS Task Role to access Bedrock services
        account_id = Stack.of(self).account
        region = Stack.of(self).region
        
        ecs_task_role = iam.Role(self, "EcsTaskExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy"),
                iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite")  # Add this line
            ]
        )
        ecs_task_role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock:*"],  # Adjust based on the specific Bedrock actions required
            resources=["*"],
        ))
        ecs_task_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:*"],  # This gives access to all S3 actions
            resources=["*"],   # This applies the actions to all resources
        ))
        ecs_task_role.add_to_policy(iam.PolicyStatement(actions=
                                                        ["secretsmanager:GetSecretValue"],
                                                         resources=[f"arn:aws:secretsmanager:{region}:{account_id}:secret:/myapp/db_credentials"] )
                                                         )
        # Grant permissions for quota monitoring
        ecs_task_role.add_to_policy(iam.PolicyStatement(
            actions=["cloudwatch:PutMetricData"],
            resources=["*"]
        ))
        ecs_task_role.add_to_policy(iam.PolicyStatement(
            actions=["sns:Publish"],
            resources=[quota_alert_topic.topic_arn]
        ))
        usage_tracking_table.grant_read_write_data(ecs_task_role)
        # Grant S3 read/write access to ECS Task Role
        bucket.grant_read_write(ecs_task_execution_role)
        # Create ECS Task Log Groups explicitly
        python_container_log_group = logs.LogGroup(self, "PythonContainerLogGroup",
                                                log_group_name="/ecs/MyFirstTaskDef/PythonContainerLogGroup",
                                                retention=logs.RetentionDays.ONE_WEEK,
                                                removal_policy=cdk.RemovalPolicy.DESTROY)

        javascript_container_log_group = logs.LogGroup(self, "JavaScriptContainerLogGroup",
                                                    log_group_name="/ecs/MySecondTaskDef/JavaScriptContainerLogGroup",
                                                    retention=logs.RetentionDays.ONE_WEEK,
                                                    removal_policy=cdk.RemovalPolicy.DESTROY)
        # ECS Task Definitions
        task_definition_1 = ecs.FargateTaskDefinition(self, "MyFirstTaskDef",
                                                      memory_limit_mib=1024,
                                                      cpu=256, execution_role=ecs_task_execution_role, task_role=ecs_task_role,
                                                     )

        container_definition_1 = task_definition_1.add_container("python_container",
                                                                  image=ecs.ContainerImage.from_registry(python_image_asset.image_uri),
                                                                  memory_limit_mib=1024,
                                                                  logging=ecs.LogDrivers.aws_logs(
        stream_prefix="PythonContainerLogs",
        log_group=python_container_log_group,
    ))

        task_definition_2 = ecs.FargateTaskDefinition(self, "MySecondTaskDef",
                                                      memory_limit_mib=1024,
                                                      cpu=256, execution_role=ecs_task_execution_role, task_role=ecs_task_role,
                                                      )

        container_definition_2 = task_definition_2.add_container("javascript_container",
                                                                  image=ecs.ContainerImage.from_registry(javascript_image_asset.image_uri),
                                                                  memory_limit_mib=1024,
                                                                   logging=ecs.LogDrivers.aws_logs(
        stream_prefix="JavaScriptContainerLogs",
        log_group=javascript_container_log_group
    ))
        model_id_image = 'us.anthropic.claude-3-5-sonnet-20241022-v2:0'
        model_id_link = 'us.anthropic.claude-3-haiku-20240307-v1:0'
        model_arn_image = f'arn:aws:bedrock:{region}:{account_id}:inference-profile/{model_id_image}'
        model_arn_link = f'arn:aws:bedrock:{region}:{account_id}:inference-profile/{model_id_link}'
        # ECS Tasks in Step Functions
        ecs_task_1 = tasks.EcsRunTask(self, "ECS RunTask",
                                      integration_pattern=sfn.IntegrationPattern.RUN_JOB,
                                      cluster=cluster,
                                      task_definition=task_definition_1,
                                      assign_public_ip=False,
                                      
                                      container_overrides=[tasks.ContainerOverride(
                                       container_definition = container_definition_1,
                                          environment=[
                                              tasks.TaskEnvironmentVariable(
                                                  name="S3_BUCKET_NAME",
                                                  value=sfn.JsonPath.string_at("$.s3_bucket")
                                              ),
                                              tasks.TaskEnvironmentVariable(
                                                  name="S3_FILE_KEY",
                                                  value=sfn.JsonPath.string_at("$.s3_key")
                                              ),
                                              tasks.TaskEnvironmentVariable(
                                                  name="S3_CHUNK_KEY",
                                                  value=sfn.JsonPath.string_at("$.chunk_key")
                                              ),
                                            tasks.TaskEnvironmentVariable(
                                                  name="model_arn_image",
                                                  value=model_arn_image
                                              ),
                                            tasks.TaskEnvironmentVariable(
                                                  name="model_arn_link",
                                                  value=model_arn_link
                                              ),
                                            tasks.TaskEnvironmentVariable(
                                                  name="AWS_REGION",
                                                  value=region
                                              ),
                                            tasks.TaskEnvironmentVariable(
                                                  name="MAX_IMAGE_SIZE",
                                                  value=os.environ.get('MAX_IMAGE_SIZE', '20000000')
                                              ),
                                            tasks.TaskEnvironmentVariable(
                                                  name="QUOTA_ALERT_SNS_TOPIC_ARN",
                                                  value=quota_alert_topic.topic_arn
                                              ),
                                            tasks.TaskEnvironmentVariable(
                                                  name="USAGE_TRACKING_TABLE",
                                                  value=usage_tracking_table.table_name
                                              ),
                                            tasks.TaskEnvironmentVariable(
                                                  name="ADOBE_API_QUOTA_LIMIT",
                                                  value=os.environ.get('ADOBE_API_QUOTA_LIMIT', '0')
                                              ),
                                          ]
                                      )],
                                      launch_target=tasks.EcsFargateLaunchTarget(
                                          platform_version=ecs.FargatePlatformVersion.LATEST
                                      ),
                                      propagated_tag_source=ecs.PropagatedTagSource.TASK_DEFINITION,
                                     )

        ecs_task_2 = tasks.EcsRunTask(self, "ECS RunTask (1)",
                                      integration_pattern=sfn.IntegrationPattern.RUN_JOB,
                                      cluster=cluster,
                                      task_definition=task_definition_2,
                                      assign_public_ip=False,
                                    
                                      container_overrides=[tasks.ContainerOverride(
                                          container_definition=container_definition_2,
                                          environment=[
                                              tasks.TaskEnvironmentVariable(
                                                  name="S3_BUCKET_NAME",
                                                  value=sfn.JsonPath.string_at("$.Overrides.ContainerOverrides[0].Environment[0].Value")
                                              ),
                                              tasks.TaskEnvironmentVariable(
                                                  name="S3_FILE_KEY",
                                                  value=sfn.JsonPath.string_at("$.Overrides.ContainerOverrides[0].Environment[1].Value")
                                              ),
                                              tasks.TaskEnvironmentVariable(
                                                  name="AWS_REGION",
                                                  value=region
                                              ),
                                          ]
                                      )],
                                      launch_target=tasks.EcsFargateLaunchTarget(
                                          platform_version=ecs.FargatePlatformVersion.LATEST
                                      ),
                                      propagated_tag_source=ecs.PropagatedTagSource.TASK_DEFINITION,
                                      )

        # Step Function Map State
        map_state = sfn.Map(self, "Map",
                            max_concurrency=100,
                            items_path=sfn.JsonPath.string_at("$.chunks"),
                            result_path="$.MapResults")

        map_state.iterator(ecs_task_1.next(ecs_task_2))

        cloudwatch_logs_policy = iam.PolicyStatement(
                    actions=["cloudwatch:PutMetricData"],  # Allow PutMetricData action
                    resources=["*"],  # All CloudWatch resources # All CloudWatch Logs resources
        )
        java_lambda = lambda_.Function(
            self, 'JavaLambda',
            runtime=lambda_.Runtime.JAVA_21,
            handler='com.example.App::handleRequest',
            code=lambda_.Code.from_asset('lambda/java_lambda/PDFMergerLambda/target/PDFMergerLambda-1.0-SNAPSHOT.jar'),
            environment={
                'BUCKET_NAME': bucket.bucket_name  # this line sets the environment variable
            },
            timeout=Duration.seconds(900),
            memory_size=1024
        )

        java_lambda.add_to_role_policy(cloudwatch_logs_policy)
        java_lambda_task = tasks.LambdaInvoke(self, "Invoke Java Lambda",
                                      lambda_function=java_lambda,
                                      payload=sfn.TaskInput.from_object({
        "fileNames.$": "$.chunks[*].s3_key"
                     }),
                                      output_path=sfn.JsonPath.string_at("$.Payload"))
        bucket.grant_read_write(java_lambda)

        # Define the Add Title Lambda function
        host_machine = platform.machine().lower()
        print("Architecture of Machine:",host_machine)
        if "arm" in host_machine:
            lambda_arch = lambda_.Architecture.ARM_64
        else:
            lambda_arch = lambda_.Architecture.X86_64

        add_title_lambda = lambda_.Function(
            self, 'AddTitleLambda',
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler='myapp.lambda_handler',
            code=lambda_.Code.from_docker_build('lambda/add_title'),
            timeout=Duration.seconds(900),
            memory_size=1024,
            # architecture=lambda_.Architecture.ARM_64
            architecture=lambda_arch,
        )

        # Grant the Lambda function read/write permissions to the S3 bucket
        bucket.grant_read_write(add_title_lambda)

        # Define the task to invoke the Add Title Lambda function
        add_title_lambda_task = tasks.LambdaInvoke(
            self, "Invoke Add Title Lambda",
            lambda_function=add_title_lambda,
            payload=sfn.TaskInput.from_object({
                "Payload.$": "$"
            })
        )

        # Add the necessary policy to the Lambda function's role
        add_title_lambda.add_to_role_policy(cloudwatch_logs_policy)
        add_title_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:*"],  # Adjust based on the specific Bedrock actions required
            resources=["*"],
        ))

        # Chain the tasks in the state machine
        # chain = map_state.next(java_lambda_task).next(add_title_lambda_task)
        
        a11y_precheck = lambda_.Function(
            self,'accessibility_checker_before_remidiation',
            runtime=lambda_.Runtime.PYTHON_3_10,
            handler='main.lambda_handler',
            code=lambda_.Code.from_docker_build('lambda/accessibility_checker_before_remidiation'),
            timeout=Duration.seconds(900),
            memory_size=512,
            architecture=lambda_arch,
        )
        
        a11y_precheck.add_to_role_policy(
            iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=[f"arn:aws:secretsmanager:{region}:{account_id}:secret:/myapp/*"]
        ))
        bucket.grant_read_write(a11y_precheck)
        a11y_precheck.add_to_role_policy(cloudwatch_logs_policy)

        a11y_precheck_lambda_task = tasks.LambdaInvoke(
            self, 
            "a11y_precheck",
            lambda_function=a11y_precheck,
            payload=sfn.TaskInput.from_json_path_at("$"),
            output_path="$.Payload"
        )

        a11y_postcheck = lambda_.Function(
            self,'accessibility_checker_after_remidiation',
            runtime=lambda_.Runtime.PYTHON_3_10,
            handler='main.lambda_handler',
            code=lambda_.Code.from_docker_build('lambda/accessability_checker_after_remidiation'),
            timeout=Duration.seconds(900),
            memory_size=512,
            architecture=lambda_arch,
        )
        
        a11y_postcheck.add_to_role_policy(
            iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=[f"arn:aws:secretsmanager:{region}:{account_id}:secret:/myapp/*"]
        ))
        bucket.grant_read_write(a11y_postcheck)
        a11y_postcheck.add_to_role_policy(cloudwatch_logs_policy)

        a11y_postcheck_lambda_task = tasks.LambdaInvoke(
            self, 
            "a11y_postcheck",
            lambda_function=a11y_postcheck,
            payload=sfn.TaskInput.from_json_path_at("$"),
            output_path="$.Payload"
        )
        
        chain = map_state.next(java_lambda_task).next(add_title_lambda_task).next(a11y_postcheck_lambda_task)

        parallel_state = sfn.Parallel(self, "ParallelState",
                                      result_path="$.ParallelResults")
        parallel_state.branch(chain)
        parallel_state.branch(a11y_precheck_lambda_task)

        log_group_stepfunctions = logs.LogGroup(self, "StepFunctionLogs",
            log_group_name="/aws/states/MyStateMachine_PDFAccessibility",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=cdk.RemovalPolicy.DESTROY
        )
        # State Machine

        state_machine = sfn.StateMachine(self, "MyStateMachine",
                                         definition=parallel_state,
                                         timeout=Duration.minutes(150),
                                         logs=sfn.LogOptions(
                                             destination=log_group_stepfunctions,
                                             level=sfn.LogLevel.ALL
                                         ))
        
        # Lambda Function
        split_pdf_lambda = lambda_.Function(
            self, 'SplitPDF',
            runtime=lambda_.Runtime.PYTHON_3_10,
            handler='main.lambda_handler',
            code=lambda_.Code.from_docker_build("lambda/split_pdf"),
            timeout=Duration.seconds(900),
            memory_size=int(os.environ.get('LAMBDA_MEMORY_SIZE', '3008')),  # Increased for large PDF processing
            environment={
                'PDF_CHUNK_SIZE': os.environ.get('PDF_CHUNK_SIZE', '200'),
                'MAX_PAGES_PER_PDF': os.environ.get('MAX_PAGES_PER_PDF', '10000'),
                'MAX_PDF_FILE_SIZE': os.environ.get('MAX_PDF_FILE_SIZE', '5368709120'),
            }
        )

        split_pdf_lambda.add_to_role_policy(cloudwatch_logs_policy)

        # S3 Permissions for Lambda
        bucket.grant_read_write(split_pdf_lambda)

        # Trigger Lambda on S3 Event
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(split_pdf_lambda),
            s3.NotificationKeyFilter(prefix="pdf/"),
            s3.NotificationKeyFilter(suffix=".pdf")
        )

        # Step Function Execution Permissions
        state_machine.grant_start_execution(split_pdf_lambda)

        # Pass State Machine ARN to Lambda as an Environment Variable
        split_pdf_lambda.add_environment("STATE_MACHINE_ARN", state_machine.state_machine_arn)
        # Store log group names dynamically
        split_pdf_lambda_log_group_name = f"/aws/lambda/{split_pdf_lambda.function_name}"
        java_lambda_log_group_name = f"/aws/lambda/{java_lambda.function_name}"
        add_title_lambda_log_group_name = f"/aws/lambda/{add_title_lambda.function_name}"
        accessibility_checker_pre_log_group_name = f"/aws/lambda/{a11y_precheck.function_name}"
        accessibility_checker_post_log_group_name = f"aws/lambda/{a11y_postcheck.function_name}"



        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        dashboard_name = f"PDF_Processing_Dashboard-{timestamp}"
        dashboard = cloudwatch.Dashboard(self, "PDF_Processing_Dashboard", dashboard_name=dashboard_name,
                                         variables=[cloudwatch.DashboardVariable(
                                            id="filename",
                                            type=cloudwatch.VariableType.PATTERN,
                                            label="File Name",
                                            input_type=cloudwatch.VariableInputType.INPUT,
                                            value="filename",
                                            visible=True,
                                            default_value=cloudwatch.DefaultValue.value(".*"),
                                        )]
                                         )
        # Add Widgets to the Dashboard
        dashboard.add_widgets(
            cloudwatch.LogQueryWidget(
                title="File status",
                log_group_names=[split_pdf_lambda_log_group_name, java_lambda_log_group_name, python_container_log_group.log_group_name,  javascript_container_log_group.log_group_name],
                query_string='''fields @timestamp, @message
                    | parse @message "File: *, Status: *" as file, status
                    | stats latest(status) as latestStatus by file
                    | sort file asc ''',
                width=24,
                height=6
            ),
            cloudwatch.LogQueryWidget(
                title="Split PDF Lambda Logs",
                log_group_names=[split_pdf_lambda_log_group_name],
                query_string='''fields @message 
                                | filter @message like /filename/''',
                width=24,
                height=6
            ),
            cloudwatch.LogQueryWidget(
                title="Step Function Execution Logs",
                log_group_names=[log_group_stepfunctions.log_group_name],
                query_string='''fields @message 
                                | filter @message like /filename/''',
                width=24,
                height=6
            ),
            cloudwatch.LogQueryWidget(
                title="ECS TASK 1 ADOBE AUTOTAG AND EXTRACT LOGS",
                log_group_names=[python_container_log_group.log_group_name],
                query_string='''fields @message 
                                | filter @message like /filename/''',
                width=24,
                height=6
            ),
            cloudwatch.LogQueryWidget(
                title="ECS TASK 2 LLM alt text generation",
                log_group_names=[javascript_container_log_group.log_group_name],
                query_string='''fields @message 
                                | filter @message like /filename/''',
                width=24,
                height=6
            ),
            cloudwatch.LogQueryWidget(
                title="Java Lambda Logs for PDF Merger",
                log_group_names=[java_lambda_log_group_name],
                query_string='''fields @message 
                                | filter @message like /filename/''',
                width=24,
                height=6
            ),
        )

        # CloudWatch Alarms for Adobe API Quota Monitoring
        # Alarm for 80% quota usage (Warning)
        quota_warning_alarm = cloudwatch.Alarm(
            self, "AdobeAPIQuotaWarning",
            alarm_name="adobe-api-quota-warning",
            alarm_description="Alert when Adobe API usage reaches 80% of quota",
            metric=cloudwatch.Metric(
                namespace="PDFAccessibility",
                metric_name="QuotaUsagePercentage",
                dimensions_map={
                    "APIName": "AdobeAPI",
                    "Period": "Monthly"
                },
                statistic="Maximum",
                period=Duration.minutes(5)
            ),
            threshold=80,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        quota_warning_alarm.add_alarm_action(cw_actions.SnsAction(quota_alert_topic))

        # Alarm for 95% quota usage (Critical)
        quota_critical_alarm = cloudwatch.Alarm(
            self, "AdobeAPIQuotaCritical",
            alarm_name="adobe-api-quota-critical",
            alarm_description="Alert when Adobe API usage reaches 95% of quota",
            metric=cloudwatch.Metric(
                namespace="PDFAccessibility",
                metric_name="QuotaUsagePercentage",
                dimensions_map={
                    "APIName": "AdobeAPI",
                    "Period": "Monthly"
                },
                statistic="Maximum",
                period=Duration.minutes(5)
            ),
            threshold=95,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        quota_critical_alarm.add_alarm_action(cw_actions.SnsAction(quota_alert_topic))

        # Alarm for quota exceeded errors
        quota_exceeded_alarm = cloudwatch.Alarm(
            self, "AdobeAPIQuotaExceeded",
            alarm_name="adobe-api-quota-exceeded",
            alarm_description="Alert when Adobe API quota is exceeded",
            metric=cloudwatch.Metric(
                namespace="PDFAccessibility",
                metric_name="APIError",
                dimensions_map={
                    "APIName": "AdobeAPI",
                    "ErrorType": "QuotaExceeded"
                },
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        quota_exceeded_alarm.add_alarm_action(cw_actions.SnsAction(quota_alert_topic))

        # Add quota monitoring widgets to the dashboard
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Adobe API Quota Usage",
                left=[
                    cloudwatch.Metric(
                        namespace="PDFAccessibility",
                        metric_name="QuotaUsagePercentage",
                        dimensions_map={
                            "APIName": "AdobeAPI",
                            "Period": "Monthly"
                        },
                        statistic="Maximum",
                        period=Duration.hours(1),
                        label="Quota Usage %"
                    )
                ],
                width=12,
                height=6
            ),
            cloudwatch.GraphWidget(
                title="Adobe API Call Status",
                left=[
                    cloudwatch.Metric(
                        namespace="PDFAccessibility",
                        metric_name="APICallStatus",
                        dimensions_map={
                            "APIName": "AdobeAPI",
                            "Status": "Success"
                        },
                        statistic="Sum",
                        period=Duration.hours(1),
                        label="Successful Calls",
                        color=cloudwatch.Color.GREEN
                    ),
                    cloudwatch.Metric(
                        namespace="PDFAccessibility",
                        metric_name="APICallStatus",
                        dimensions_map={
                            "APIName": "AdobeAPI",
                            "Status": "Failure"
                        },
                        statistic="Sum",
                        period=Duration.hours(1),
                        label="Failed Calls",
                        color=cloudwatch.Color.RED
                    )
                ],
                width=12,
                height=6
            )
        )

        # Export SNS topic ARN and DynamoDB table name for reference
        cdk.CfnOutput(self, "QuotaAlertTopicArn",
            value=quota_alert_topic.topic_arn,
            description="SNS Topic ARN for quota alerts",
            export_name="pdf-accessibility-quota-alert-topic-arn"
        )
        cdk.CfnOutput(self, "UsageTrackingTableName",
            value=usage_tracking_table.table_name,
            description="DynamoDB table for usage tracking",
            export_name="pdf-accessibility-usage-tracking-table"
        )

app = cdk.App()
PDFAccessibility(app, "PDFAccessibility")
app.synth()
