import "./index.css";

import { createApp } from "vue";
import { frappeRequest, resourcesPlugin, setConfig } from "frappe-ui";

import App from "./App.vue";
import router from "./router";

setConfig("resourceFetcher", frappeRequest);

const app = createApp(App);
app.use(router);
app.use(resourcesPlugin);
app.mount("#app");
