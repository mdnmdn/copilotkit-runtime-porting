import { createServer } from 'node:http';
import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNodeHttpEndpoint,
    GoogleGenerativeAIAdapter,
} from '@copilotkit/runtime';
import * as dotenv from 'dotenv';

dotenv.config();

const serviceAdapter = new ExperimentalEmptyAdapter();


// console.log({GOOGLE_API_KEY: process.env.GOOGLE_API_KEY!})
// const serviceAdapter = new GoogleGenerativeAIAdapter({
//     apiKey: process.env.GOOGLE_API_KEY!,
//     model: 'gemini-2.5-flash-lite'
// });

  const runtime = new CopilotRuntime({
    remoteEndpoints: [
      { url: "http://localhost:8000/copilotkit" },
    ],
      observability_c : {
          enabled : true ,
          progressive : false ,
          hooks : {
              handleRequest : async (data) => {
                  console.log("handleRequest", data);
              },
              handleError : async (data) => {
                  console.error("handleError", data);
              },
              handleResponse : async (data) => {
                  console.log("handleResponse", data);
              }
          }
      }
  });

  const handler = copilotRuntimeNodeHttpEndpoint({
    endpoint: '/copilotkit',
    runtime,
    serviceAdapter,
  });

const server = createServer((req, res) => {
  console.log("request", req.url);

  return handler(req, res);
});

server.listen(4000, () => {
  console.log('Listening at http://localhost:4000/copilotkit');
});