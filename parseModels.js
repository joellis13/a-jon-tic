const modelObj = require("./models-info.json");

models = modelObj["data"];

const template =
  "alias cdspro='COPILOT_PROVIDER_BASE_URL=https://api.fireworks.ai/inference/v1 \
  COPILOT_PROVIDER_API_KEY=fw_5iNB6sP4sve9h9GyZ5ZxS5 \
  COPILOT_MODEL=%MODEL% \
  copilot'\n\n";

let counter = 0;

const aliases = models
  .filter((model) => model.supports_tools)
  .map((model) => {
    console.log(model);
    counter++;
    modelId = model.id;

    return template.replace("%MODEL%", modelId);
  });

console.log(`Model Count: ${counter}`);
console.log(aliases);
