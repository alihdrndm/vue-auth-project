import { defineComponent, h } from "vue";
import {
  createRouter,
  createWebHistory,
  type RouteRecordRaw,
} from "vue-router";

const Placeholder = defineComponent({
  name: "PlaceholderView",
  setup: () => () => h("h1", "Eingang"),
});

export const routes: RouteRecordRaw[] = [
  { path: "/", name: "home", component: Placeholder },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});
