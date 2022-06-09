/* eslint-disable no-unused-vars */
import Vue from "vue";
import Vuex from "vuex";
import axios from "./axios-auth";
import globalAxios from "axios";
import router from "./router";

Vue.use(Vuex);

export default new Vuex.Store({
  state: {
    // userList: [],
    idToken: null,
    userId: null
    // user: null
  },
  mutations: {
    pushUser(state, user) {
      state.user = user;
    },

    authUser(state, userData) {
      state.idToken = userData.ourToken;
      state.userId = userData.ourUserId;
    },

    clearUserData(state) {
      state.idToken = null;
      state.userId = null;
    }
  },
  actions: {
    setLogoutTimer({ commit }, expirationTime) {
      setTimeout(() => {
        commit("clearUserData");
        router.replace("/signin");
      }, expirationTime * 1000);
    },

    signup({ commit, dispatch }, authData) {
      axios
        .post(":signUp?key=AIzaSyCfxOoxcxAwdtkxFMNWeTYj-GjMD5dnQ_w", {
          email: authData.email,
          password: authData.password,
          returnSecureToken: true
        })
        .then(res => {
          console.log(res);
          commit("authUser", {
            ourToken: res.data.idToken,
            ourUserId: res.data.localId
          });
          const now = new Date();
          const expirationDate = new Date(
            now.getTime() + res.data.expiresIn * 1000
          );
          localStorage.setItem("token", res.data.idToken);
          localStorage.setItem("userId", res.data.localId);
          localStorage.setItem("expirationDate", expirationDate);
          dispatch("storeUser", authData);
          dispatch("setLogoutTimer", res.data.expiresIn);
          router.replace("/dashboard");
        })
        .catch(error => console.log(error));
    },

    login({ commit, dispatch }, authData) {
      axios
        .post(
          ":signInWithPassword?key=AIzaSyCfxOoxcxAwdtkxFMNWeTYj-GjMD5dnQ_w",
          {
            email: authData.email,
            password: authData.password,
            returnSecureToken: true
          }
        )
        .then(res => {
          console.log(res);
          commit("authUser", {
            ourToken: res.data.idToken,
            ourUserId: res.data.localId
          });
          const now = new Date();
          const expirationDate = new Date(
            now.getTime() + res.data.expiresIn * 1000
          );
          localStorage.setItem("token", res.data.idToken);
          localStorage.setItem("userId", res.data.localId);
          localStorage.setItem("expirationDate", expirationDate);
          dispatch("setLogoutTimer", res.data.expiresIn);
        })
        .catch(error => console.log(error));
    },

    tryAutoLogin({ commit }) {
      const token = localStorage.getItem("token");
      if (!token) {
        return;
      }
      const expirationDate = localStorage.getItem("expirationDate");
      const now = new Date();
      if (now >= expirationDate) {
        return;
      }
      const userId = localStorage.getItem("userId");
      commit("authUser", {
        ourToken: token,
        ourUserId: userId
      });
    },

    storeUser({ commit, state }, userData) {
      if (!state.idToken) {
        return;
      }
      globalAxios
        .post("/user.json" + "?auth=" + state.idToken, userData)
        .then(res => console.log(res))
        .catch(error => console.log(error));
    },

    // fetchUser({ commit, state }) {
    //   if (!state.idToken) {
    //     return;
    //   }
    //   globalAxios
    //     .get("/user.json" + "?auth=" + state.idToken)
    //     .then(res => {
    //       console.log(res);
    //       const data = res.data;
    //       const users = [];
    //       for (let key in data) {
    //         const user = data[key];
    //         user.id = key;
    //         users.push(user);
    //       }
    //       commit("pushUser", users[0]);
    //     })
    //     .catch(error => console.log(error));
    // },

    logout({ commit }) {
      commit("clearUserData");
      localStorage.removeItem("expirationDate");
      localStorage.removeItem("userId");
      localStorage.removeItem("token");
      router.replace("/signin");
    }
  },

  getters: {
    user(state) {
      return state.user;
    },
    isAuthenticated(state) {
      return state.idToken !== null;
    }
  }
});
