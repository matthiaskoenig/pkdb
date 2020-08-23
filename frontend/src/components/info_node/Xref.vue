<template>
  <!-- FIXME: add search highlight -->
  <v-chip
          class="ma-1"
          color="black"
          outlined
          pill
          small
          :href="url"
  >

    <strong><text-highlight :queries="highlight">{{ name }}</text-highlight> </strong>| <text-highlight :queries="highlight">{{ accession}}</text-highlight>

  </v-chip>
</template>

<script>
export default {
  name: "Xref",
  props: {
    name: {
      type: String,
      required: true,
    },
    accession: {
      type: String,
      required: true,
    },
    url: {
      type: String,
      required: true,
    }
  },
  computed:
      {
    highlight(){
      return this.$store.state.highlight
    },
  }
}
</script>

<style scoped>

</style>