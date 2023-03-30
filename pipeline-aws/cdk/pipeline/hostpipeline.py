from aws_cdk import core
import aws_cdk.core
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_iam as iam
import aws_cdk.aws_codecommit as codecommit
import aws_cdk.aws_codepipeline as codepipeline
import aws_cdk.aws_codebuild as codebuild
import aws_cdk.aws_codepipeline_actions as codepipeline_actions
import os

class CdkPipelinedeployStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, vpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        name = "Codedeploy-to-ec2"

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
        
        # We need to get the ECR image 
        pipeline.add_stage(
            stage_name="Deploy",
            actions=[
                codepipeline_actions.CloudFormationCreateReplaceChangeSetAction(
                    action_name="PrepareChanges",
                    stack_name="codedeploy-stack",
                    change_set_name="codedeploy-stack-set-name",
                    admin_permissions=True,
                    template_path=source_output.at_path("Dev-ec2.yml"),
                    run_order=1
                ),
                codepipeline_actions.ManualApprovalAction(
                    action_name="ApproveChanges",
                    run_order=2
                ),
                codepipeline_actions.CloudFormationExecuteChangeSetAction(
                    action_name="ExecuteChanges",
                    stack_name="codedeploy-stack",
                    change_set_name="codedeploy-stack-set-name",
                    run_order=3
                )
            ]
        )
        
        # Outputs
        core.CfnOutput(
            scope=self,
            id="application_repository",
            value=codecommit_repo.repository_clone_url_http
        )