<template>
  <div>
    <h1>{{ msg }}</h1>
    <h2>About</h2>
    <p>
      Pharmacokinetics database<br />
      Version: {{ version }}<br />
      <a href="/api/v1/" target="_blank">REST API</a>
    </p>
  </div>
</template>

<script>
export default {
  name: 'About',
  props: {
    msg: String
  }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
h3 {
  margin: 40px 0 0;
}
ul {
  list-style-type: none;
  padding: 0;
}
li {
  display: inline-block;
  margin: 0 10px;
}
a {
  color: #42b983;
}
</style>
