/* eslint-disable no-unused-vars */
import Vue from "vue";
import Vuex from "vuex";
import axios from "./axios-auth";
import globalAxios from "axios";

Vue.use(Vuex);

export default new Vuex.Store({
  state: {
    userList: [],
    idToken: null,
    // userId: null
    user: null
  },
  mutations: {
    pushUser(state, user) {
      state.user = user;
    },
    authUser(state, userData) {
      state.idToken = userData.ourToken;
      state.userId = userData.ourUserId;
    }
  },
  actions: {
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
          dispatch("storeUser", authData);
        })
        .catch(error => console.log(error));
    },
    login({ commit }, authData) {
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
        })
        .catch(error => console.log(error));
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
    fetchUser({ commit, state }) {
      if (!state.idToken) {
        return;
      }
      globalAxios
        .get("/user.json" + "?auth=" + state.idToken)
        .then(res => {
          console.log(res);
          const data = res.data;
          const users = [];
          for (let key in data) {
            const user = data[key];
            user.id = key;
            users.push(user);
          }
          commit("pushUser", users[0]);
        })
        .catch(error => console.log(error));
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
