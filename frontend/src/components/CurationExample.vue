<template>
  <div>
  <h2>Example study</h2>
    <p align="justify">
      The following example shows what information is extracted from a typical study
    </p>
    <p>
  <v-img src="/assets/images/pkexample2.png" width="100%" class="mb-2">
    <v-sheet  color="rgb(255,255,255, 0.9)"  rounded class="text-on-image text-caption text-right pl-2 pr-2" >
      <v-spacer/>
      RV Patwardhan, P V Desmond, R F Johnson, S Schenker
      <v-spacer/>
      <span class="font-italic text">
          The Journal of Laboratory and clinical medicine, 1980-05-30
        </span>
    </v-sheet>
  </v-img>
    </p>
    <p>
    <v-btn color="black"
           text
           width="100%"
           title="Show PK-DB data for example study"
           v-on:click="load_example"
    >
      <v-icon left color="#1E90FF">{{ faIcon('data') }}</v-icon>
      Example study
    </v-btn>
  </p>
  </div>
</template>

<script>
import {IconsMixin} from "@/icons";

export default {
  name: "CurationExample",
  mixins: [IconsMixin],
  methods: {
    load_example() {
      console.error("query !!!")
      let example = [
        {
          "query_type": "queries",
          "key": "studies__sid__in",
          "value": [{"name": "Patwarddhan1980", "sid": "PKDB00057",}]
        },
      ]
      this.reset()
      for (let q of example) {
        this.update_store(q)
      }
      this.$router.push("/data")
    },
    reset() {
      this.$store.commit('resetQuery');
    },
    update_store(q) {
      this.$store.dispatch('updateQueryAction', {
        query_type: q.query_type,
        key: q.key,
        value: q.value,
      })
    }
  },
}
</script>

<style scoped>
  .text-on-image {
    margin-right: 0;
    float: right;
    position:absolute;
    bottom: 0;
    right: 0;
  }
</style>