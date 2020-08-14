<template>
  <!-- FIXME: add search highlight -->
  <v-chip
          class="ma-1"
          color="black"
          outlined
          pill
          small
          :href="xref.url"
  >

    <strong><text-highlight :queries="highlight">{{ xref.name }}</text-highlight> </strong>| <text-highlight :queries="highlight">{{ xref.accession}}</text-highlight>

  </v-chip>
</template>

<script>
export default {
  name: "Xref",
  props: {
    xref: {
      type: Object,
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