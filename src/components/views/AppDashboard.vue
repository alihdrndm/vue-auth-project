<template>
  <div id="dashboard">
    <h1>Dashboard</h1>
    <p><strong>You are here because you're authenticated</strong></p>
    <div class="btn-cntnr">
      <button @click="showUsers">Show Users</button>
    </div>
    <br />
    <hr />
    <p v-for="user in userList" :key="user.id">{{ user.name }}</p>
  </div>
</template>

<script>
import axios from "axios";
export default {
  data() {
    return {
      // userEmail: ""
      userList: []
    };
  },

  methods: {
    showUsers() {
      axios
        .get("/users.json")
        .then(res => {
          console.log(res);
          const data = res.data;
          // const users = [];
          for (let key in data) {
            const user = data[key];
            user.id = key;
            this.userList.push(user);
          }
          // this.userEmail = users[0].email;
        })
        .catch(error => console.log(error));
    }
  }
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
