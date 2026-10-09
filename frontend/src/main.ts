import { VueQueryPlugin } from "@tanstack/vue-query";
import { createPinia } from "pinia";
import { createApp } from "vue";

import { createQueryClient } from "./api/query";
import App from "./App.vue";
import { createAppRouter } from "./router";

const app = createApp(App);
// Pinia comes first: the router guard reads the session store.
app.use(createPinia());
app.use(createAppRouter());
app.use(VueQueryPlugin, { queryClient: createQueryClient() });
app.mount("#app");
