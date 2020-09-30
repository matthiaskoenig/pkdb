<template>
    <div id="comments" v-if="comments && comments.length>0">

        <div v-for="comment in comments" :key="comment.pk" style="text-align: justify; color: white">
                  <user-avatar :username="comment.username" />
                    {{comment.text}}
        </div>
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