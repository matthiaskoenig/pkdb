<template>
  <!-- FIXME: add search highlight -->
  <v-chip
      class="ma-1"
      color="black"
      dark
      pill
      small
      :href="annotation.url"
  >
    {{annotation.relation}}|<strong>{{annotation.collection}}</strong>|{{ annotation.term }}
  </v-chip>
</template>

<script>
export default {
  name: "Annotation",
  props: {
    annotation: {
      type: Object,
      required: true,
    }
  }

}
</script>

<style scoped>

</style>