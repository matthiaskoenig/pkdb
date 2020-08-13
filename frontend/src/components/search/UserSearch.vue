<!--
not yet implemented.
-->
<template>

  <multiselect
      v-model="selected_entries"
      :options="users"
      :close-on-select="false"
      :clear-on-select="false"
      :preserve-search="true"
      :placeholder="placeholder"
      track-by="username"
      :multiple="true"
      :custom-label="customLabel"
      :searchable="true">

    <template slot="tag" slot-scope="{ option, remove }">
        <span class="multiselect__tag">
           <user-avatar :user="option"
           />
          <span  @click="remove(option)">
            <i class="multiselect__tag-icon"></i>
          </span>
        </span>
    </template>
    <template
        slot="option"
        slot-scope="props"
    >
           <user-avatar :user="props.option"
           ></user-avatar>
      {{props.option.first_name}}  {{props.option.last_name}}
    </template>
   <span slot="noResult">No results found.</span>

  </multiselect>
</template>

<script>
import Multiselect from 'vue-multiselect'

export default {
  name: "CreatorSearch",
  components: {
    Multiselect
  },
  data () {

    return {
      users : [
        {"username":"mkoenig","first_name":"Matthias","last_name":"König"},
        {"username": "janekg", "first_name": "Jan", "last_name": "Grzegorzewski",},
        {"username":"dimitra","first_name":"Dimitra","last_name":"Eleftheriadou"},
        {"username": "kgreen","first_name": "Kathleen","last_name": "Green",},
        {"username": "jbrandhorst","first_name": "Janosch",  "last_name": "Brandhorst",},
        {"username": "FlorBar","first_name": "Florian", "last_name": "Bartsch",},
        {"username": "deepa", "first_name": "Deepa", "last_name": "Maheshvare",},
        {"username": "yduport", "first_name": "Yannick","last_name": "Duport",},
        {"username": "adriankl", "first_name": "Adrian", "last_name": "Koeller",},
        {"username": "dannythekey", "first_name": "Danny", "last_name": "Ke",},
        {"username": "SaraD-hub",  "first_name": "Sara","last_name": "De Angelis",},

      ],
      selected_entries: [],
    }
  },
  props:{
    on: {
      type: String,
      required:true
    }},

  computed: {
    placeholder: function () {
      return  "Search for " + this.on.charAt(0).toUpperCase() + this.on.slice(1)
    },
    query_key : function () {
      return   "studies__" + this.on+"__in"
    }
  },

  watch:{
    selected_entries() {
      var query_dict = {}
      query_dict[this.query_key] = this.selected_entries.map(x => x.username)
      this.$emit('selected_entries',query_dict)
    }
  },
  methods: {
    clearAll() {
      this.selected_entries = []
    },
    customLabel({first_name, last_name}) {
      return `${first_name} – ${last_name}`
    }
  }
}
</script>
