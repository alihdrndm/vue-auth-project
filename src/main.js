/* eslint-disable no-unused-vars */
import Vue from "vue";
import App from "./App.vue";
import router from "./router";
import axios from "axios";
import store from "./store";

Vue.config.productionTip = false;

axios.defaults.baseURL =
  "https://vue-project-auth-55555-default-rtdb.firebaseio.com";
// axios.defaults.headers.common["Authorization"] = "given";
// axios.defaults.headers.get["Accepts"] = "application.json";

// eslint-disable-next-line no-unused-vars
const reqInterceptor = axios.interceptors.request.use(config => {
  // config.headers["Authorization"] = "not given";
  console.log("ReqInterceptor", config);
  return config;
});

const resInterceptor = axios.interceptors.response.use(res => {
  console.log("ResInterceptor", res);
  return res;
});

// axios.interceptors.request.eject(reqInterceptor);
// axios.interceptors.response.eject(resInterceptor);

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount("#app");
