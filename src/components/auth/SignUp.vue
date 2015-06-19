<template>
  <div id="signup">
    <div class="signup-form">
      <form @submit.prevent="onSubmit">
        <div class="input">
          <label for="name">Your Name</label>
          <input type="text" id="name" required v-model="name" />
        </div>
        <div class="input">
          <label for="email">Email Address</label>
          <input type="email" id="email" required v-model="email" />
        </div>
        <div class="input">
          <label for="phone">Phone Number</label>
          <input type="tel" id="phone" required v-model="phone" />
        </div>
        <div class="input">
          <label for="password">Password</label>
          <input type="password" id="password" required v-model="password" />
        </div>
        <div class="input">
          <label for="confirm-password">Confirm Password</label>
          <input
            type="password"
            id="confirm-password"
            required
            v-model="confirmPassword"
          />
        </div>
        <div class="submit">
          <button type="submit">Submit</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      name: "",
      email: "",
      phone: "",
      password: "",
      confirmPassword: ""
    };
  },
  methods: {
    onSubmit() {
      const formData = {
        name: this.name,
        email: this.email,
        phone: this.phone,
        password: this.password,
        confirmPassword: this.confirmPassword
      };
      console.log(formData);
      this.$store.dispatch("signup", {
        email: formData.email,
        password: formData.password
      });
    }
  }
};
</script>

<style scoped>
.signup-form {
  width: 400px;
  margin: 30px auto;
  border: 1px solid #eee;
  border-radius: 6px;
  padding: 20px;
  box-shadow: 0 2px 3px #ccc;
}

.input {
  margin: 10px auto;
}

.input label {
  display: block;
  color: #4e4e4e;
  margin-bottom: 6px;
}

.input input {
  font: inherit;
  width: 100%;
  height: 36px;
  padding: 6px 12px;
  box-sizing: border-box;
  border: 1px solid #ccc;
  border-radius: 6px;
}

.input input:focus {
  outline: none;
  border: 1px solid #13575a;
  background-color: #eee;
}

.submit button {
  border: 1px solid #13575a;
  border-radius: 6px;
  color: #13575a;
  padding: 10px 20px;
  font: inherit;
  cursor: pointer;
}

.submit button:hover,
.submit button:active {
  background-color: #13575a;
  color: white;
}
</style>
