<!--
vue-multiselect element
-->
<template>

  <multiselect
      :value="selected_entries"
      :options="users"
      :close-on-select="true"
      :clear-on-select="false"
      :preserve-search="true"
      :placeholder="placeholder"
      track-by="username"
      :multiple="true"
      :custom-label="customLabel"
      @input = update_store
      :searchable="true"
  >

    <template slot="tag" slot-scope="{ option, remove }">
        <span class="multiselect__tag">
           <user-avatar :user="option"
           />
          <span @click="remove(option)">
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
      {{ props.option.first_name }} {{ props.option.last_name }}
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
  data() {
    return {
      users: [
          // FIXME: NO HARD-CODING OF USERS
        {"username": "mkoenig", "first_name": "Matthias", "last_name": "König"},
        {"username": "janekg", "first_name": "Jan", "last_name": "Grzegorzewski",},
        {"username": "dimitra", "first_name": "Dimitra", "last_name": "Eleftheriadou"},
        {"username": "kgreen", "first_name": "Kathleen", "last_name": "Green",},
        {"username": "jbrandhorst", "first_name": "Janosch", "last_name": "Brandhorst",},
        {"username": "FlorBar", "first_name": "Florian", "last_name": "Bartsch",},
        {"username": "deepa", "first_name": "Deepa", "last_name": "Maheshvare",},
        {"username": "yduport", "first_name": "Yannick", "last_name": "Duport",},
        {"username": "adriankl", "first_name": "Adrian", "last_name": "Koeller",},
        {"username": "dannythekey", "first_name": "Danny", "last_name": "Ke",},
        {"username": "SaraD-hub", "first_name": "Sara", "last_name": "De Angelis",},
        {"username": "balcisue", "first_name": "Sükrü", "last_name": "Balci",},
        {"username": "paula-ogata", "first_name": "Paula", "last_name": "Ogata",},
        {"username": "lepujolh", "first_name": "Helen", "last_name": "Leal",},
        {"username": "stemllb", "first_name": "Beatrice", "last_name": "Stemmer Mallol",},
        {"username": "jonaspk98", "first_name": "Jonas", "last_name": "Küttner",},
        {"username": "xresearch", "first_name": "XResearch", "last_name": "Group",},
      ],
    }
  },
  props: {
    on: {
      type: String,
      required: true
    }
  },
  computed: {
    placeholder: function () {
      return "Select by " + this.on.charAt(0).toUpperCase() + this.on.slice(1)
    },
    query_key: function () {
      return "studies__" + this.on + "__in"
    },
    selected_entries() {
      return this.$store.state.queries_users[this.query_key]
    }
  },

  methods: {
    update_store(value){
      this.$store.dispatch('updateQueryAction', {
        query_type:"queries_users",
        key: this.query_key,
        value: value,
      })
    },

    customLabel({first_name, last_name}) {
      return `${first_name} – ${last_name}`
    }
  }
}
</script>
