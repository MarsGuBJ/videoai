import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import { statusClass, levelClass, priorityClass } from "./store";
import "./styles/global.css";

const app = createApp(App);
app.config.globalProperties.statusClass = statusClass;
app.config.globalProperties.levelClass = levelClass;
app.config.globalProperties.priorityClass = priorityClass;
app.use(router);
app.mount("#app");
