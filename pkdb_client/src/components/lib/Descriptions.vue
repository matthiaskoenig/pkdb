<template>
    <div id="descriptions" v-if="descriptions && descriptions.length>0">
            <v-card flat dark>
                <span class="attr">Descriptions</span><br/>
            </v-card>
            <template v-for="(item, index) in descriptions">

                <v-card flat>
                    <v-icon small>fas fa-align-left</v-icon>&nbsp;&nbsp;
                    {{item.text}}
                </v-card>
                <br />
            </template>
    </div>
</template>

<script>
    export default {
        name: "Descriptions",
        props: {
            descriptions: {
                type: Array,
            }
        }
    }
</script>

<style scoped>
</style>