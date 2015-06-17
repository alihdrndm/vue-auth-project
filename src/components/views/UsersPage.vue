<template>
  <div>
    <h1>The user page</h1>
    <hr />
    <p>Loaded ID: {{ id }}</p>
    <hr />
    <button @click="navigateToHome">Go to Home</button>
  </div>
</template>

<script>
export default {
  data() {
    return {
      id: this.$route.params.id
    };
  },
  methods: {
    navigateToHome() {
      this.$router.push({ name: "home" });
    }
  }
};
</script>
