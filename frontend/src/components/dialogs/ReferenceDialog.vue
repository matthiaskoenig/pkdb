<template>
  <v-dialog
      v-model="show"
      max-width="600"
  >
    <v-card
        color="white"
    >
      <v-flex  xs8>
        <v-card-text>
          <div>{{ data.item.sid }}</div>
          <v-card-title>
            {{data.item.title}}
          </v-card-title>
          <div class="text--primary">
            {{data.item.abstract}}
          </div>
        </v-card-text>
        <v-card-actions>
          <v-btn color="primary" flat @click.stop="showReferenceDialog=false">Close</v-btn>
        </v-card-actions>
      </v-flex>
      <v-flex xs4>
      </v-flex>
    </v-card>
  </v-dialog>




</template>

<script>

export default {
  name: "ReferenceDialog",
  data () {

    return {
      showReferenceDialog: false,
    }
  },
  props: {
    data: Object,
    visible: Boolean,
  },
  computed: {
    show: {
      get () {
        return this.visible
      },
      set (value) {
        if (!value) {
          this.$emit('close')
        }
      }
    }
  }
}
</script>

<style scoped>

</style>