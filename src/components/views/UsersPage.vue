<template>
  <div class="user-page">
    <h1>The user page</h1>
    <hr />
    <p>Loaded ID: {{ id }}</p>
    <hr />
    <div class="btn-cntnr">
      <button @click="navigateToHome">Go to Home</button>
    </div>
    <br />
    <hr />
    <div class="user-list">
      <p v-for="(user, index) in userList" :key="user.id">
        User Name: {{ user.name }}
        <span>
          <router-link
            :to="{ name: 'details', params: { user: user, id: index + 1 } }"
            exact
            >Show Details</router-link
          >
        </span>
      </p>
    </div>
  </div>
</template>

<script>
import globalAxios from "axios";
export default {
  data() {
    return {
      id: this.$route.params.id,
      userList: []
    };
  },
  created() {
    this.showUsers();
  },
  watch: {
    $route(to) {
      this.id = to.params.id;
    }
  },
  methods: {
    navigateToHome() {
      this.$router.push({ name: "home" });
    },
    showUsers() {
      globalAxios
        .get("/user.json" + "?auth=" + this.$store.state.idToken)
        .then(res => {
          console.log(res);
          const data = res.data;
          for (let key in data) {
            const user = data[key];
            user.id = key;
            this.userList.push(user);
          }
        })
        .catch(error => console.log(error));
      // this.$store.dispatch("fetchUser");
    }
  }
};
</script>

<style scoped>
.user-page,
.user-list {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.user-list {
  align-items: flex-start;
}

.btn-cntnr button {
  border: 1px solid #13575a;
  border-radius: 6px;
  color: #13575a;
  padding: 10px 20px;
  margin-top: 10px;
  font: inherit;
  cursor: pointer;
}

.btn-cntnr button:hover,
.btn-cntnr button:active {
  background-color: #13575a;
  color: white;
}
</style>
