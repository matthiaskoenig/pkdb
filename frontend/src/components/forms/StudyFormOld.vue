<template>

  <v-card>
    <v-card-text>
      <v-autocomplete
          v-model="selected_studies"
          :disabled="isUpdating"
          :items="studies"
          :loading="isLoading"
          :search-input.sync="search"
          color="white"
          item-text="sid"
          item-value="name"
          label="Studies"
          placeholder="Start typing to Search"
          multiple
          filled
          chips
      >
        <template v-slot:selection="data">
          <v-chip
              :input-value="data.input-value"
              close
              class="chip--select-multi"
              @input="remove(data.item)"
          >
            {{ data.item.name }}

          </v-chip>
        </template>

        <template>
          <v-list-tile-content>
            <v-list-tile-title v-html="data.item.sid"></v-list-tile-title>
            <v-list-tile-sub-title v-html="data.item.name"></v-list-tile-sub-title>
          </v-list-tile-content>
        </template>
      </v-autocomplete>
    </v-card-text>
    <v-divider></v-divider>

  </v-card>
</template>


<script>

export default {
  name: "StudyForm",
  data: () => ({
    descriptionLimit: 60,
    autoUpdate: true,
    isUpdating: false,
    studies: [],
    isLoading: false,
    selected_studies: [],
    search: null,
  }),

  computed: {
    study_url() {
      return this.$store.state.endpoints.api  + 'studies' + '/?format=json'
    },

    fields () {
      if (!this.model) return []

      return Object.keys(this.model).map(key => {
        return {
          key,
          value: this.selected_studies[key] || 'n/a',
        }
      })
    },
    items () {
      return this.studies.map(entry => {
        const sid = entry.sid
        return Object.assign({}, entry, { sid })
      })
    },
  },
  methods: {
    remove (item) {
      const index = this.selected_studies.indexOf(item.sid)
      if (index >= 0) this.sid.splice(index, 1)
    }
  },
  watch: {
    search () {
      console.log(this.items)
      // Items have already been loaded
      if (this.items.length > 0) return

      // Items have already been requested
      if (this.isLoading) return

      this.isLoading = true

      // Lazily load input items
      fetch(this.study_url)
          .then(res => res.json())
          .then(res => {
            this.count =  res.data.count
            this.studies =  res.data.data
          })
          .catch(err => {
            console.log(err)
          })
          .finally(() => (this.isLoading = false))
    },
  },
}
</script>