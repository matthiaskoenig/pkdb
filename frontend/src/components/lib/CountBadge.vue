<template>
  <v-badge
      color="black"
      :content="count.toString()"
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
    count: 0
  },
}
</script>

<style scoped>

</style>
