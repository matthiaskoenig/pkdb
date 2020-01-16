<template>
    <div id="descriptions" v-if="descriptions && descriptions.length>0">
        <template v-for="description in descriptions">
            <span :key="description">
            <v-avatar title="description" :size="32">
                <v-icon small color="black">fas fa-align-left</v-icon>&nbsp;&nbsp;
            </v-avatar> {{description.text}} <br /></span>
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