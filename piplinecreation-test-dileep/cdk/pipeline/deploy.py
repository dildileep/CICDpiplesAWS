from aws_cdk import core
import aws_cdk.core
import aws_cdk.core.Stack as Stack
from aws_cdk import (
    # Duration,
#    core.Stack,
    aws_codepipeline as codepipeline,
    aws_codedeploy as codedeploy,
    aws_codecommit as codecommit,
    aws_codepipeline_actions as codepipeline_actions,
    aws_iam as iam
    # aws_sqs as sqs,
)

from constructs import Construct

class EnidoMarvellTestStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        main_respository_name = 'marvell-apps-v3'
        ec2_name = f"{main_respository_name}-ec2"

        repo = codecommit.Repository(self, "Marvell-Repo",
            repository_name=main_respository_name,
            code=codecommit.Code.from_zip_file('app.zip')
        )

        source_output = codepipeline.Artifact("SourceArtifact")
        pipeline = codepipeline.Pipeline(
            scope=self, 
            id=f"{main_respository_name}-pipeline",
            pipeline_name=f"{main_respository_name}-generic-pipeline",
        )

        source_action = codepipeline_actions.CodeCommitSourceAction(
            action_name="Source",
            repository=repo,
            output=source_output,
            branch="main"
            # trigger=codepipeline_actions.CodeCommitTrigger.POLL
        )

        pipeline.add_stage(
            stage_name="Source",
            actions=[source_action]
        )

        # Deploy
        deploy_application = codedeploy.ServerApplication(self, "CodeDeployApplication", 
            application_name=f"{main_respository_name}-Application",
        )

        codedeploy_role = iam.Role(self, "CodeDeployRole",
            assumed_by=iam.ServicePrincipal("codedeploy.amazonaws.com"),
        )
        codedeploy_role.add_to_policy(iam.PolicyStatement(
            resources=["*"],
            actions=["ec2:*", "autoscaling:*"]
        ))

        deployment_group = codedeploy.ServerDeploymentGroup(self, "DeploymentGroup",
            application=deploy_application,
            deployment_config=codedeploy.ServerDeploymentConfig.ALL_AT_ONCE,
            install_agent=True,
            role=codedeploy_role,
            ec2_instance_tags=codedeploy.InstanceTagSet({
                "Name": [ec2_name]
            })
        )
        
        #Add deploy Stage
        # we need to send repository_uri + instance name of the ec2

        deploy_action = codepipeline_actions.CloudFormationCreateUpdateStackAction(
            action_name="CloudFormationCreateUpdate",
            stack_name=f"{main_respository_name}-stack",
            template_path=source_output.at_path("template.yaml"),
            admin_permissions=True,
            replace_on_failure=True,
            parameter_overrides={'InstanceName': ec2_name}
        )

        pipeline.add_stage(
            stage_name="Deploy",
            actions=[deploy_action]
        )