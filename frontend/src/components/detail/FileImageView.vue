<template>
  <v-container max-width="200">
    <v-tabs
        v-model="active"
        show-arrows
        color="#999999"
        dark
        slider-size ="width"
    >
      <v-tab
          v-for="(item, i) in files"
          :key="i"
          ripple
      >
        {{ id_from_name(item.name) }}
      </v-tab>
      <v-tab-item v-for="item in files" :key="item.name">
        <get-file :resource_url="backend+item.file">
          <template slot-scope="data">
            <v-img :src="data.data"
                   class="mt-1"
                   width="392"
                   :alt="item.name"
                   :contain="true"
                   @click="next"
            />
          </template>
        </get-file>
      </v-tab-item>
    </v-tabs>

  </v-container>

</template>

<script>
    /**
     * Displaying files from the database.
     */
    import {UrlMixin} from "../tables/mixins";
    import GetFile from "../api/GetFile";

    export default {
        name: "FileImageView",
        components: {
            GetFile
        },
        props: {
            files: {
                type: Array,
                required: true,
            }
        },
        mixins:[UrlMixin],
        data () {
            return {
                active: null,
            }
        },
        computed: {
            backend(){
                    return this.$store.state.django_domain;
                },
            images() {
                var list = [];
                for (var k=0; k<this.files.length; k++){
                    var item = this.files[k];
                    if (item.name.endsWith("png")){
                        list.push(item)
                    }
                }
                return list.sort(function(a, b){
                    return a.name.localeCompare(b.name)
                });

            }
        },
        methods: {
            id_from_name: function (name) {
                let tokens = name.split("_");
                let id = tokens[tokens.length-1];
                id = id.split(".")[0];
                return id
            },
            next () {
                const active = parseInt(this.active);
                this.active = (active < (this.images.length-1) ? active + 1 : 0)
            }
        }
    }
</script>
<style scoped>
</style>