<template>
  <div>
    <h1>Reference</h1>
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
