import WelcomePage from "./components/views/WelcomePage.vue";
import SignUp from "./components/auth/SignUp.vue";
import SignIn from "./components/auth/SignIn.vue";
import AppDashboard from "./components/views/AppDashboard.vue";
import UsersPage from "./components/views/UsersPage.vue";
import UserDetails from "./components/views/UserDetails.vue";
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
        router.go("1");
        // router.replace("/signin");
        // alert("You are already logged in");
      }
    }
  },
  {
    path: "/signup",
    component: SignUp,
    beforeEnter: (to, from, next) => {
      if (!localStorage.getItem("token")) {
        // router.push("/dashboard");
        next();
      } else {
        router.go(-1);
      }
    }
  },
  {
    path: "/signin",
    component: SignIn,
    beforeEnter: (to, from, next) => {
      if (!localStorage.getItem("token")) {
        // router.push("/dashboard");
        next();
      } else {
        router.go(-1);
      }
    }
  },
  {
    path: "/dashboard",
    name: "home",
    component: AppDashboard,
    beforeEnter: (to, from, next) => {
      if (localStorage.getItem("token")) {
        next();
      } else {
        router.go(-1);
      }
    }
  },
  {
    path: "/users/:id",
    name: "users",
    component: UsersPage,
    beforeEnter: (to, from, next) => {
      if (localStorage.getItem("token")) {
        next();
      } else {
        router.go(-1);
      }
    }
  },
  {
    path: "/details",
    name: "details",
    component: UserDetails,
    props: true
  }
];

export default routes;
