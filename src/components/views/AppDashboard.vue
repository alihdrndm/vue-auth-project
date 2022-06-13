<template>
  <div id="dashboard">
    <h1>Dashboard</h1>
    <p><strong>You are here because you're authenticated</strong></p>
    <!-- <div class="btn-cntnr">
      <button @click="showUsers">Show Users</button>
    </div> -->
    <br />
    <hr />
    <!-- <p v-for="(user, index) in userList" :key="user.id">
      User Name: {{ user.name }}
      <span>
        <router-link
          :to="{ name: 'details', params: { user: user, id: index + 1 } }"
          exact
          >Show Details</router-link
        >
      </span>
    </p> -->
  </div>
</template>

<script>
// import globalAxios from "axios";
export default {
  // data() {
  //   return {
  //     userList: []
  //   };
  // },
  // computed: {
  //   email() {
  //     return !this.$store.getters.user ? false : this.$store.getters.user.email;
  //   }
  // },
  // created() {
  //   this.showUsers();
  // },
  // methods: {
  //   showUsers() {
  //     globalAxios
  //       .get("/user.json" + "?auth=" + this.$store.state.idToken)
  //       .then(res => {
  //         console.log(res);
  //         const data = res.data;
  //         for (let key in data) {
  //           const user = data[key];
  //           user.id = key;
  //           this.userList.push(user);
  //         }
  //       })
  //       .catch(error => console.log(error));
  //     // this.$store.dispatch("fetchUser");
  //   }
  //   // doSomething() {
  //   //   console.log("Did you do something?");
  //   //   this.$router.go("/details");
  //   // }
  // }
};
</script>

<style scoped>
h1,
p {
  text-align: center;
}

p {
  color: rgb(40, 121, 38);
}

.btn-cntnr {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
