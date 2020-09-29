<template>
    <div id="comments" v-if="comments && comments.length>0">

        <span v-for="comment in comments" :key="comment.pk">
                <p  align="justify" xs11>
                  <user-avatar :username="comment.username" />

                    {{comment.text}}
                </p>
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