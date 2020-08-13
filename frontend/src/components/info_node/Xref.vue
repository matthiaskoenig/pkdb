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
    <strong>{{ xref.name }}</strong>|{{ xref.accession}}
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
  }

}
</script>

<style scoped>

</style>