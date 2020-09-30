<template>

  <v-card class="parent_color pa-0 ma-0"
      v-if="(item.comments && item.comments.length>0) || (item.descriptions && item.descriptions.length>0)"
      flat
      dark
  >
    <v-card-title>{{ title }}</v-card-title>
    <v-card-text>
      <descriptions v-if="item.descriptions" :descriptions="item.descriptions"/>
      <comments v-if="item.comments" :comments="item.comments"/>
    </v-card-text>
  </v-card>

</template>

<script>
    export default {
        name: "Annotations",
        props: {
            item: {
                type: Object,
                required: true
            },
            title: {
              type: String,
              required: true
            },
        }
    }
</script>

<style scoped>

</style>