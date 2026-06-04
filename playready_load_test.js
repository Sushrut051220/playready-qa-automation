import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 5,
  duration: '30s',
};

const BASE_URL = "https://dev-playready-fdry-public.services.ai.azure.com/api/projects/dev-playready-fdry-public-proj/agents/PublicAgent/runs";

export default function () {

  const payload = JSON.stringify({
    input: {
      messages: [
        {
          role: "user",
          content: "What is PlayReady DRM?"
        }
      ]
    }
  });

  const params = {
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${__ENV.AUTH_TOKEN}`
    }
  };

  const res = http.post(BASE_URL, payload, params);

  console.log(`status: ${res.status}`);
  console.log(`latency: ${res.timings.duration} ms`);

  check(res, {
    "status is 200 or 202": (r) => r.status === 200 || r.status === 202,
  });

  sleep(1);
}
