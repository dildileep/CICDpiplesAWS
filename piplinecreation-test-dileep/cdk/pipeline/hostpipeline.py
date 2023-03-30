from aws_cdk import core
import aws_cdk.core
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_iam as iam
import aws_cdk.aws_codecommit as codecommit
import aws_cdk.aws_codepipeline as codepipeline
import aws_cdk.aws_codebuild as codebuild
import aws_cdk.aws_codepipeline_actions as codepipeline_actions
import aws_cdk.aws_codedeploy as code_deploy
import os

class CdkPipelinedeployStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, vpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        name = "Codedeploy-to-ec2"
        ec2_name = f"{name}-dil"

        # ECR repositories

        
        # Repo for Application
        codecommit_repo = codecommit.Repository(
            scope=self, 
            id=f"{name}-container-git",
            repository_name=f"{name}",
            description=f"Deployment code"
        )

        pipeline = codepipeline.Pipeline(
            scope=self, 
            id=f"{name}-container--pipeline",
            pipeline_name=f"{name}"
        )

        source_output = codepipeline.Artifact()
        docker_output_arm64 = codepipeline.Artifact("ARM64_BuildOutput")
        manifest_output = codepipeline.Artifact("ManifestOutput")

        source_action = codepipeline_actions.CodeCommitSourceAction(
            action_name="CodeCommit_Source",
            repository=codecommit_repo,
            output=source_output,
            branch="master"
        )
        
        pipeline.add_stage(
            stage_name="Source",
            actions=[source_action]
        )
        
        deploy_action = codepipeline_actions.CloudFormationCreateUpdateStackAction(
            action_name=f"{name}-cloudformation",
            stack_name=f"{name}-cloudformation",
#            change_set_name=f"{name}-cloudformation",
            admin_permissions=True,
            template_path=source_output.at_path("Dev-ec2.yml"),
#            role=action_role
        )
        # 
#        deploy_action = codepipeline_actions.CloudFormationCreateUpdateStackAction(
#            action_name=f"{name}-cloudformation",
#            stack_name=f"{name}-cloudformation",
#            template_path=source_output.at_path("Dev-ec2.yml"),
#            admin_permissions=True,
#            replace_on_failure=True,
#            parameter_overrides={'InstanceName': ec2_name}
#        )

        pipeline.add_stage(
            stage_name="Deploy-ec2",
            actions=[deploy_action]
        )
        
        deploy_stage = pipeline.add_stage(stage_name="Deploy-code")
        deploy_stage.add_action(
            codepipeline_actions.CodeDeployServerDeployAction(
                deployment_group=code_deploy.ServerDeploymentGroup.from_server_deployment_group_attributes(
                    self,
                    "server_code_deploy_group",
                    application=code_deploy.ServerApplication.from_server_application_name(self,"server_app",server_application_name="WebappApplication"),
                    deployment_group_name="WebappDeploymentGroup",
                ),
                action_name="Deploy",
                input=source_output
            )
        )
        
        
        # Outputs
        core.CfnOutput(
            scope=self,
            id="application_repository",
            value=codecommit_repo.repository_clone_url_http
        )