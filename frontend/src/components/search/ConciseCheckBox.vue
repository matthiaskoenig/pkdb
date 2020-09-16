<template>
  <v-checkbox
      type="checkbox"
      class="ma-0"
      v-model="concise"
      @click.stop=""
      label="Concise"
      hide-details
      hint="Concises the data."
  ></v-checkbox>
</template>
<script>
export default {
  name: "ConciseCheckBox",
  computed: {
    concise: {
      get(){
        return this.$store.state.concise
      },
      set(value) {
        this.$store.dispatch('updateAction', {
          key: "concise",
          value: value,
        })
      }
    }
  }
}
</script>

<style scoped>

</style>