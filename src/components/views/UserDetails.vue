<template>
  <div class="cntnr-div">
    <p>name: {{ user.name }}</p>
    <p>email: {{ user.email }}</p>
    <p>telephone: {{ user.phone }}</p>
    <p>{{ id }}</p>
  </div>
</template>

<script>
export default {
  props: ["user"],
  data() {
    return {
      id: this.$route.params.id
    };
  },

  mounted() {
    console.log(this.$route);
    console.log(this.user);
  },

  watch: {
    $route(to) {
      this.id = to.params.id;
    }
  }
};
</script>

<style scoped>
.cntnr-div {
  margin: 30px auto;
  padding: 20px;
  width: 400px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  border: 1px solid #eee;
  border-radius: 6px;
  box-shadow: 0 2px 3px #ccc;
}
</style>
