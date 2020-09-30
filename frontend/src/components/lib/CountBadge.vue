<template>
  <v-badge
      :color="color"
      :content="count.toString()"
      :bottom="bottom"
  >
    {{ text }}
  </v-badge>

</template>

<script>
export default {
  name: "CountBadge",
  props: {
    text: {
      type: String,
      required: true
    },
    color: {
      type: String,
      default: "black"
    },
    bottom: {
      type: Boolean,
      default: false
    },
    count: 0
  },

}
</script>

<style scoped>

</style>
