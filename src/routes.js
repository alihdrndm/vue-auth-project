import WelcomePage from "./components/views/WelcomePage.vue";
import SignUp from "./components/auth/SignUp.vue";
import SignIn from "./components/auth/SignIn.vue";
import AppDashboard from "./components/views/AppDashboard.vue";

const routes = [
  { path: "/", component: WelcomePage },
  { path: "/signup", component: SignUp },
  { path: "/signin", component: SignIn },
  { path: "./dashboard", component: AppDashboard }
];

export default routes;
