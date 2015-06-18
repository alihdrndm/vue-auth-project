import WelcomePage from "./components/views/WelcomePage.vue";
import SignUp from "./components/auth/SignUp.vue";
import SignIn from "./components/auth/SignIn.vue";
import AppDashboard from "./components/views/AppDashboard.vue";
import store from "./store";
import router from "./router";

const routes = [
  {
    path: "/",
    component: WelcomePage,
    beforeEnter: (to, from, next) => {
      if (!store.state.idToken) {
        next();
      } else {
        router.go(1);
      }
    }
  },
  { path: "/signup", component: SignUp },
  { path: "/signin", component: SignIn },
  {
    path: "/dashboard",
    component: AppDashboard,
    beforeEnter: (to, from, next) => {
      if (store.state.idToken) {
        next();
      } else {
        router.go(1);
      }
    }
  }
];

export default routes;
