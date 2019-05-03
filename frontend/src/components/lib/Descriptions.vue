<template>
    <div id="descriptions" v-if="descriptions && descriptions.length>0">
        <template v-for="(item, index) in descriptions">

            <v-card flat>
                <v-icon small>fas fa-align-left</v-icon>&nbsp;&nbsp;
                {{item.text}}
            </v-card>
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