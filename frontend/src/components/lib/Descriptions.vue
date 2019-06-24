<template>
    <div id="descriptions" v-if="descriptions && descriptions.length>0">
        <template v-for="(item, index) in descriptions">
            <v-avatar title="description" :size="32">
                <v-icon small color="black">fas fa-align-left</v-icon>&nbsp;&nbsp;
            </v-avatar> {{item.text}}<br />
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