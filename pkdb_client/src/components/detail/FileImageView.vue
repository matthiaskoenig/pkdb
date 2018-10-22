<template>
<span>
    <v-tabs
            v-model="active"
            color="primary"
            dark
            slider-color="yellow">
        <v-tab
                v-for="(item, i) in images"
                :key="i"
                ripple
        >
            {{ id_from_name(item.name) }}

        </v-tab>
        <v-tab-item v-for="item in images" :key="item.name">
            <v-card flat>
                <a :href="item.file" target="blank">{{ item.name }}</a>
                <v-img :src="item.file" max-height="500" max-width="500" :alt="item.name" :contain="true" @click="next"></v-img>
            </v-card>

        </v-tab-item>
    </v-tabs>

    </span>
</template>

<script>
    /**
     * Displaying files from the database.
     */
    import {lookup_icon} from "@/icons"

    export default {
        name: "FileImageView",
        components: {},
        props: {
            files: {
                type: Array,
                required: true,
            }
        },
        data () {
            return {
                active: null,
            }
        },
        computed: {
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
            icon: function (key) {
                return lookup_icon(key)
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