<template>
    <div id="comments" v-if="comments && comments.length>0">
        <span v-for="comment in comments">
            <v-layout row wrap>
                <v-flex xs1>
                    <user-avatar :user="comment.user"/>
                </v-flex>
                <v-flex xs11>
                    {{comment.text}}
                </v-flex>
            </v-layout>
        </span>
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