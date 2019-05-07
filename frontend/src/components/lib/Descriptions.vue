<template>
    <div id="descriptions" v-if="descriptions && descriptions.length>0">
        <template v-for="(item, index) in descriptions">

            <v-layout row wrap>
                <v-flex xs1>
                    <v-avatar :title="description" :size="32">
                        <v-icon small color="black">fas fa-align-left</v-icon>&nbsp;&nbsp;
                    </v-avatar>
                </v-flex>
                <v-flex xs11>
                    {{item.text}}
                </v-flex>
            </v-layout>

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