/* eslint-disable no-unused-vars */
import Vue from "vue";
import Vuex from "vuex";
import axios from "./axios-auth";

Vue.use(Vuex);

export default new Vuex.Store({
  state: {
    idToken: null,
    userId: null
  },
  mutations: {
    authUser(state, userData) {
      state.idToken = userData.ourToken;
      state.userId = userData.ourUserId;
    }
  },
  actions: {
    signup({ commit }, authData) {
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
    }
  },
  getters: {}
});
