<template>
  <div>
    <h1>About</h1>
    <p>
      Pharmacokinetics database<br />
      Version: {{ version }}<br />
      <a href="http://www.pk-db.com/api/v1/" target="_blank">REST API</a>
    </p>
    <h2>Contact</h2>
    <p>
    <ul>
      <li>Email: {{ email }}</li>
      <li>Website: {{ web }}</li>
    </ul>
    </p>
  </div>
</template>

<script>
export default {
  name: 'About',
  props: {
    msg: String
  },
  data(){
    return {
        email: 'konigmatt@googlemail.com',
        web: 'https://livermetabolism.com'
    }
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
