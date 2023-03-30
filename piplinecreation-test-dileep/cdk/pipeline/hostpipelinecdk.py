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

#from aws_cdk import (core,aws_codedeploy as code_deploy,)
import os
import random

class CdkPipelinedeployStackhost1(core.Stack):
    # create a role assign an existing service role, using the arn
    def createRole(self,policyArn,servicePrincipal,roleName):
        iamRole = iam.Role(
            self,
            "role" + str(random.random()),
            role_name=roleName,
            assumed_by=iam.ServicePrincipal(servicePrincipal,),
        )
    
        iamRole.add_managed_policy(
            iam.ManagedPolicy.from_managed_policy_arn(
                self, "managedpolicy" + str(random.random()), managed_policy_arn=policyArn
            )
        )

        #print(iam.Role.role_arn)
        return iamRole.role_arn

    def __init__(self, scope: core.Construct, id: str, vpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        name = "Codedeploy-to-ec2"
        vpcId = vpc
        instanceName = "MyCodePipelineDemoec2"
        instanceType = "t2.micro"
        amiName = "amzn2-ami-kernel-5.10-hvm-2.0.20221103.3-x86_64-gp2"
        keyPair = "key_dil"
        #roleArn = props["ec2role"]
        env={
            'account': os.environ['CDK_DEFAULT_ACCOUNT'], 
            'region': os.environ['CDK_DEFAULT_REGION']
        }
        #env = kwargs['env']
        userData = "yum -y update; yum install -y ruby aws-cli; \
        cd /home/ec2-user; aws s3 cp s3://aws-codedeploy-ap-south-1/latest/install . --region ap-south-1; \
        chmod +x install; ./install auto"
        
        # Instance Role and SSM Managed Policy
        roleArn = iam.Role(self, "InstanceSSM", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"))
        
        roleArn.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))
        
        #security group
        sec_group = ec2.SecurityGroup(self, "sec-group",security_group_name="sg_pipelinedemo", vpc=vpc, allow_all_outbound=True)
        
        #security group rules own ip
        #sec_group.add_ingress_rule(peer=ec2.Peer.ipv4("<replace with your ip cidrblock>"),description="Allow SSH connection",connection=ec2.Port.tcp(22))
        #security group rules own ip HTTP acess
        #sec_group.add_ingress_rule(peer=ec2.Peer.ipv4("<replace with your ip cidrblock>"),description="Allow HTTP connection",connection=ec2.Port.tcp(80))

        # ECR repositories
        ec2_instance = ec2.Instance(
            self,
            "ec2-instance",
            instance_name=instanceName,
            instance_type=ec2.InstanceType(instanceType),
            machine_image=ec2.MachineImage().lookup(name=amiName),
            vpc=vpc,
            security_group=sec_group,
            key_name=keyPair,
            role=roleArn

        )

        # attach the custom user data
        ec2_instance.add_user_data(userData)

        # add a tag
        core.Tag.add(self, key="Name", value="MyCodePipelineDemo")
        
        # create a server application
        serverApplication = code_deploy.ServerApplication(self, "MyDemoApplication", application_name="MyDemoApplication")
        
        
        # call the createRole function
        deployroleArn = self.createRole("arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole","codedeploy","CodeDeployRole")
        
        # Create a server application (CodeDeploy Application that deploys to EC2/on-premise instances.)
        serverApplication = code_deploy.ServerApplication(self, "MyDemoApplication", application_name="MyDemoApplication")
        
        
        # ServerDeploymentGroup = A CodeDeploy Deployment Group that deploys to EC2/on-premise instances.
        # This group uses the ec2 tag assigned earlier to limit deployments on those instances
        code_deploy.ServerDeploymentGroup(
            self,
            "CodeDeploymentGroup",
            application=serverApplication,
            deployment_group_name="MyDemoDeploymentGroup",
            role=iam.Role.from_role_arn(self, "role", role_arn=roleArn),
            deployment_config=code_deploy.ServerDeploymentConfig.ONE_AT_A_TIME,
            ec2_instance_tags=code_deploy.InstanceTagSet(
                # any instance with tags satisfying
                # key1=v1 or key1=v2 or key2 (any value) or value v3 (any key)
                # will match this group
                {"Name": ["MyCodePipelineDemo"],},
            ),
        )
        
        pipeline = codepipeline.Pipeline(
            scope=self, 
            id=f"{name}-container--pipeline",
            pipeline_name=f"{name}"
        )
        source_output = codepipeline.Artifact()
        
        source_stage = pipeline.add_stage(stage_name="Source")
        deploy_stage = pipeline.add_stage(stage_name="Deploy")
        
        source_stage.add_action(
            codepipeline_actions.CodeCommitSourceAction(
                action_name="Source",
                repository=codecommit.Repository.from_repository_name(self,"code_repo",repository_name="MyDemoRepo"),
                run_order=1,
                output=source_output,
            )
        )
        
        deploy_stage.add_action(
            codepipeline_actions.CodeDeployServerDeployAction(
                deployment_group=code_deploy.ServerDeploymentGroup.from_server_deployment_group_attributes(
                    self,
                    "server_code_deploy_group",
                    application=code_deploy.ServerApplication.from_server_application_name(self,"server_app",server_application_name="MyDemoApplication"),
                    deployment_group_name="MyDemoDeploymentGroup",
                ),
                action_name="Deploy",
                input=source_output
            )
        )
        
        
        
        # Repo for Application
        #codecommit_repo = codecommit.Repository(scope=self,id=f"{name}-container-git",repository_name=f"{name}",description=f"Deployment code")
        
        codecommit_repo = codecommit.Repository(self, "CodeCommitRepository",repository_name="MyDemoRepo")
        
        
        # Outputs
        core.CfnOutput(
            scope=self,
            id="application_repository",
            value=codecommit_repo.repository_clone_url_http
        )