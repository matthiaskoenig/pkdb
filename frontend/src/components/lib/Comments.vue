<template>
    <div id="comments" v-if="comments && comments.length>0">
        <v-layout row wrap>
        <span v-for="comment in comments">
                <v-flex xs1>
                    <user-avatar :user="comment.user"/>
                </v-flex>
                <v-flex xs11>
                    {{comment.text}}
                </v-flex>
        </span>
        </v-layout>
    </div>
</template>

<script>
    export default {
        name: "Comments",
        props: {
            comments: {
                type: Array,
                required:true,
            }
        }
    }
</script>

<style scoped>

</style>