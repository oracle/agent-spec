# GitLab CI Integration

## Overview

This folder contains Giltab CI/CD configurations and supporting files. It contains jobs that are designed to interface with Jenkins, allowing manual trigger jobs to initiate Jenkins pipelines from within Gitlab. The folder includes:
- GitLab CI manual jobs

Currently, we support three key pipelines:
- **Regression Pipeline** – for running regression tests

Each job is a scheduler that initiates a corresponding Jenkins pipeline.

## Getting Started

This guide helps you understand the structure, setup, and usage of the GitLab CI integration with Jenkins. 

## Prerequisites

- Access to the Gitlab repository hosted in **Gitlab**
- Jenkins access token to trigger pipelines
- Gitlab project access token
- Proper configuration in the Jenkins job to accept remote triggers

## Configuration

1. update the `.gitlab/jobs` folder to add your jobs and update `.gitlab-ci.yml` file to include or reference manual jobs you added.
2. Ensure Jenkins is configured to accept remote builds via token or webhook.
3. Link Jenkins job names and parameters in the GitLab job scripts as needed.
4. Add required environment variables in GitLab CI/CD settings (e.g., `GITLAB_MERGE_BOT_TOKEN`, `JENKINS_BOT_AUTH`).

for more details about configuration please follow this Page

## How to Use the Jobs

### Regression Pipeline

This pipeline is triggered manually ,and it's responsibility is to trigger the regression pipeline in jenkins.


