<template>
  <div>
    <h1>Reference</h1>
    <dl class="row">
    <dt class="col-sm-3">Sid</dt>
    <dd class="col-sm-9">{{reference.sid}}</dd>

    <dt class="col-sm-3">Pmid</dt>
    <dd class="col-sm-9">{{reference.pmid}}</dd>


    <dt class="col-sm-3">Doi</dt>
    <dd class="col-sm-9">{{reference.doi}}</dd>

    <dt class="col-sm-3">Name</dt>
    <dd class="col-sm-9">{{reference.name}}</dd>

    <dt class="col-sm-3">Abstract</dt>
    <dd class="col-sm-9">{{reference.abstract}}</dd>

    <dt class="col-sm-3">Title</dt>
    <dd class="col-sm-9">{{reference.title}}</dd>

    <dt class="col-sm-3">Date</dt>
    <dd class="col-sm-9">{{reference.date}}</dd>

    <dt class="col-sm-3">Authors</dt>
    <dd class="col-sm-9">
      <p v-for="author in reference.authors">{{ author.first_name }} {{ author.last_name }}</p>
    </dd>

    <dt class="col-sm-3">Authors</dt>
    <dd class="col-sm-9"><a v-bind:href="reference.pdf">{{reference.pdf}}</a> </dd>
  </dl>


    {{reference}}
  </div>
</template>

<script>
import axios from 'axios';
export default {
  name: 'Study',
  data() {
    return {
      reference:"",
      errors: []
    }
  },
  mounted() {
    axios.get(`http://localhost:8000/api/v1/references/862649/?format=json`)
      .then(response => {
        // JSON responses are automatically parsed.
        this.reference = response.data
      })
      .catch(e => {
        this.errors.push(e)
      })

    // async / await version (created() becomes async created())
    //
    // try {
    //   const response = await axios.get(`http://jsonplaceholder.typicode.com/posts`)
    //   this.posts = response.data
    // } catch (e) {
    //   this.errors.push(e)
    // }

  }
}
</script>

<style scoped>

</style>
