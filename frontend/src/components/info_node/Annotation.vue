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
    <text-highlight :queries="highlight">
        {{annotation.relation}}
    </text-highlight> |
    <strong>
      <text-highlight :queries="highlight">
        {{annotation.collection}}
      </text-highlight>
    </strong>|
    <text-highlight :queries="highlight">
      {{ annotation.term }}
    </text-highlight>
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
  },
  computed:{
    highlight(){
      return this.$store.state.highlight
    },
  }

}
</script>

<style scoped>

</style>