#!/usr/bin/env bash
# Deploy the mesh to Cloud Run: three specialists first, then the orchestrator wired to
# their public URLs. The Gemini key is read from Secret Manager secret "gemini-api-key".
#
#   PROJECT=my-project REGION=asia-south1 ./deploy/cloudrun.sh
#
# Demo setup: services are public. For production use --no-allow-unauthenticated and
# have the orchestrator send ID tokens to the specialists.
set -euo pipefail

PROJECT=${PROJECT:?set PROJECT}
REGION=${REGION:-us-central1}
IMAGE="$REGION-docker.pkg.dev/$PROJECT/mesh/a2a-agent-mesh:latest"
SECRETS="GOOGLE_API_KEY=gemini-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest"

gcloud artifacts repositories describe mesh --project "$PROJECT" --location "$REGION" >/dev/null 2>&1 \
  || gcloud artifacts repositories create mesh --project "$PROJECT" --location "$REGION" \
       --repository-format docker
gcloud builds submit --project "$PROJECT" --tag "$IMAGE" .

# deploy <service> <port> <command> <args> [extra env]
deploy() {
  gcloud run deploy "$1" --project "$PROJECT" --region "$REGION" --image "$IMAGE" \
    --port "$2" --command "$3" --args "$4" \
    --set-env-vars "HOST=0.0.0.0${5:+,$5}" --set-secrets "$SECRETS" \
    --allow-unauthenticated --quiet >/dev/null
  gcloud run services describe "$1" --project "$PROJECT" --region "$REGION" \
    --format 'value(status.url)'
}

FLIGHTS_URL=$(deploy flights-agent 8001 python "-m,mesh.agents.flights")
HOTELS_URL=$(deploy hotels-agent 8002 python "-m,mesh.agents.hotels")
ACTIVITIES_URL=$(deploy activities-agent 8003 python "-m,mesh.agents.activities")

# Each specialist must advertise its own public URL in its agent card.
gcloud run services update flights-agent --project "$PROJECT" --region "$REGION" \
  --update-env-vars "FLIGHTS_URL=$FLIGHTS_URL" --quiet
gcloud run services update hotels-agent --project "$PROJECT" --region "$REGION" \
  --update-env-vars "HOTELS_URL=$HOTELS_URL" --quiet
gcloud run services update activities-agent --project "$PROJECT" --region "$REGION" \
  --update-env-vars "ACTIVITIES_URL=$ACTIVITIES_URL" --quiet

PLANNER_URL=$(deploy trip-planner 8000 adk "web,--host,0.0.0.0,--port,8000,mesh" \
  "FLIGHTS_URL=$FLIGHTS_URL,HOTELS_URL=$HOTELS_URL,ACTIVITIES_URL=$ACTIVITIES_URL")

echo "Trip planner UI: $PLANNER_URL"
