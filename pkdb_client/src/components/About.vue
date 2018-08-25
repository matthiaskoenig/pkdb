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
      <li>Email: <a :href="'mailto:'+email" target="_blank">{{email}}</a></li>
      <li>Website: <a :href="web" target="_blank">{{web}}</a></li>
    </ul>
    </p>
  </div>
</template>

<script>
import axios from 'axios'
export default {
  name: 'About',
  props: {
    msg: String
  },
  data(){
    return {
        version: "-",
        email: 'konigmatt@googlemail.com',
        web: 'https://livermetabolism.com',
        statistics: null,
        errors: []
    }
  },
    mounted() {
        axios.get(`http://localhost:8000/api/v1/statistics/?format=json`)
            .then(response => {
                // JSON responses are automatically parsed.
                this.statistics = response.data
                this.version = this.statistics["version"]
            })
            .catch(e => {
                this.errors.push(e)
            })
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
