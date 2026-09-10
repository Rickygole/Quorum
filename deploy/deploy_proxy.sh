#!/usr/bin/env bash
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
FN="${QUORUM_FN:-quorum-invoke-proxy}"
ROLE="${QUORUM_ROLE:-quorum-invoke-proxy-role}"
ORIGINS="${QUORUM_ALLOWED_ORIGINS:-https://rickygole.github.io,https://quorum-peach.vercel.app}"
RUNTIME_ARN="${QUORUM_RUNTIME_ARN:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"

echo "account $ACCOUNT region $REGION"

if ! aws iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE" \
    --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam attach-role-policy --role-name "$ROLE" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  aws iam put-role-policy --role-name "$ROLE" --policy-name invoke-agentcore \
    --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["bedrock-agentcore:InvokeAgentRuntime"],"Resource":"*"}]}'
  echo "created role, waiting for propagation"
  sleep 15
fi
ROLE_ARN="arn:aws:iam::${ACCOUNT}:role/${ROLE}"

BUILD="$(mktemp -d)"
cp "$HERE/invoke_proxy.py" "$BUILD/"
cp "$HERE/../eval/agent_decisions.json" "$BUILD/agent_decisions.json"
(cd "$BUILD" && zip -qr package.zip .)

if aws lambda get-function --function-name "$FN" --region "$REGION" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$FN" --zip-file "fileb://$BUILD/package.zip" --region "$REGION" >/dev/null
  aws lambda wait function-updated --function-name "$FN" --region "$REGION"
  aws lambda update-function-configuration --function-name "$FN" --region "$REGION" \
    --environment "Variables={QUORUM_RUNTIME_ARN=$RUNTIME_ARN,QUORUM_ALLOWED_ORIGINS=$ORIGINS}" \
    --timeout 60 --memory-size 512 >/dev/null
else
  aws lambda create-function --function-name "$FN" --region "$REGION" \
    --runtime python3.12 --role "$ROLE_ARN" --handler invoke_proxy.handler \
    --zip-file "fileb://$BUILD/package.zip" --timeout 60 --memory-size 512 \
    --environment "Variables={QUORUM_RUNTIME_ARN=$RUNTIME_ARN,QUORUM_ALLOWED_ORIGINS=$ORIGINS}" >/dev/null
  aws lambda wait function-active --function-name "$FN" --region "$REGION"
fi

aws lambda put-function-concurrency --function-name "$FN" --region "$REGION" \
  --reserved-concurrent-executions 2 >/dev/null

if ! aws lambda get-function-url-config --function-name "$FN" --region "$REGION" >/dev/null 2>&1; then
  aws lambda create-function-url-config --function-name "$FN" --region "$REGION" \
    --auth-type NONE --cors "AllowOrigins=${ORIGINS//,/ },AllowMethods=GET POST OPTIONS,AllowHeaders=content-type" >/dev/null
  aws lambda add-permission --function-name "$FN" --region "$REGION" \
    --statement-id public-url --action lambda:InvokeFunctionUrl \
    --principal '*' --function-url-auth-type NONE >/dev/null
fi

URL="$(aws lambda get-function-url-config --function-name "$FN" --region "$REGION" --query FunctionUrl --output text)"
rm -rf "$BUILD"
echo "endpoint: $URL"
